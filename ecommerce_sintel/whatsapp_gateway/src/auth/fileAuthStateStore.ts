/**
 * src/auth/fileAuthStateStore.ts
 *
 * Fase 4 del plan -- AuthenticationStateStore real, propio, para reemplazar
 * `useMultiFileAuthState` (que el propio Baileys y el plan marcan
 * explicitamente como "no recomendado para produccion", ver
 * README.md/AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md).
 *
 * Interfaz exacta pedida por la Fase 4 del plan:
 *   AuthStateStore: getCreds() / saveCreds() / getKeys() / setKeys() /
 *   removeKeys() / clear() / exists()
 *
 * ## Decision de diseno: volumen de archivos, no PostgreSQL directo
 *
 * La Fase 4 del plan prefiere PostgreSQL "si se puede aislar correctamente
 * la estructura criptografica". Se descarta aqui a proposito porque la
 * Decision #4 de la seccion 0 del plan es una regla dura: "El gateway NO
 * accedera directamente a PostgreSQL de Django". Conectar este servicio a
 * la BD de Django (aunque fuera a una tabla/esquema separado) viola esa
 * regla o exige levantar un Postgres NUEVO solo para esto -- infraestructura
 * no justificada todavia mientras el gateway sigue sin conectarse a
 * produccion ni a Docker (Fase 21, no ejecutada). Se implementa entonces la
 * alternativa que el propio plan sanciona explicitamente: "Docker named
 * volume... solo si se garantiza: persistencia, backup, permisos,
 * aislamiento, single-writer, recuperacion" -- las 5 garantias reales:
 *
 * - persistencia: escritura atomica (write tmp + rename), sobrevive un
 *   `docker restart`/crash a mitad de escritura sin corromper el archivo.
 * - backup: un unico directorio autocontenido (WA_AUTH_STORAGE_DIR),
 *   respaldable con el mismo patron que ya usa el proyecto
 *   (`ecommerce_sintel/deploy/backup.sh` respalda directorios completos).
 * - permisos: directorio 0700, archivos 0600 (mejor esfuerzo en Windows,
 *   real en el host Linux real de produccion).
 * - aislamiento: directorio propio de este servicio, nunca compartido con
 *   Django ni con ningun otro proceso.
 * - single-writer: lock de archivo con PID, con deteccion de lock
 *   huerfano (proceso que ya no existe) para permitir recuperacion tras un
 *   crash sin intervencion manual.
 *
 * Nunca se guarda esto en `src/`, `frontend/`, `git/`, `logs/` (regla dura
 * de la Fase 4/20) -- ver .gitignore de este paquete.
 */
import { randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, rename, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import {
  BufferJSON,
  initAuthCreds,
  makeCacheableSignalKeyStore,
  proto,
  type AuthenticationCreds,
  type AuthenticationState,
  type SignalDataSet,
  type SignalDataTypeMap,
} from "@whiskeysockets/baileys";

import { logger } from "../logger.js";

const DIR_MODE = 0o700;
const FILE_MODE = 0o600;

function keyFileName(type: string, id: string): string {
  // Mismo saneo real que usa la implementacion de referencia de Baileys
  // (use-multi-file-auth-state.js) -- '/' y ':' no son validos en nombres
  // de archivo en todos los filesystems (Windows en particular).
  const safeId = id.replace(/\//g, "__").replace(/:/g, "-");
  return `${type}-${safeId}.json`;
}

async function atomicWriteFile(filePath: string, data: string): Promise<void> {
  // Bug real encontrado en produccion (2026-09-22, primera sesion QR real
  // pareada de verdad): Baileys dispara varios `creds.update` casi
  // simultaneos durante el pairing/login, cada uno llamando saveCreds()
  // para el MISMO creds.json sin serializacion entre si. El nombre de tmp
  // file solo con pid+Date.now() (resolucion de milisegundos) podia
  // colisionar entre 2 llamadas concurrentes del mismo proceso -- la
  // segunda pisaba el tmp file de la primera, y cuando la primera
  // intentaba renombrarlo ya no existia (ENOENT). Esa excepcion, dentro de
  // un handler async de EventEmitter (socket.ev.on('creds.update', ...)),
  // se volvia una unhandled promise rejection -- Node la trata como fatal
  // por defecto y tumbaba el proceso completo, en loop, cada vez que
  // Baileys reintentaba. randomUUID() garantiza un nombre unico real por
  // llamada, sin importar cuantas ocurran en el mismo milisegundo.
  const tmpPath = `${filePath}.tmp-${process.pid}-${randomUUID()}`;
  await writeFile(tmpPath, data, { mode: FILE_MODE });
  await rename(tmpPath, filePath); // atomico en el mismo volumen (POSIX y NTFS)
}

async function readJsonIfExists<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await readFile(filePath, { encoding: "utf-8" });
    return JSON.parse(raw, BufferJSON.reviver) as T;
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw err;
  }
}

export class FileAuthStateStore {
  private readonly rootDir: string;
  private readonly keysDir: string;
  private readonly credsPath: string;
  private readonly lockPath: string;
  private lockHeld = false;

  constructor(rootDir: string) {
    this.rootDir = rootDir;
    this.keysDir = path.join(rootDir, "keys");
    this.credsPath = path.join(rootDir, "creds.json");
    this.lockPath = path.join(rootDir, ".lock");
  }

  private async ensureDirs(): Promise<void> {
    await mkdir(this.rootDir, { recursive: true, mode: DIR_MODE });
    await mkdir(this.keysDir, { recursive: true, mode: DIR_MODE });
  }

  /**
   * Single-writer real (Fase 4): falla si otro proceso vivo ya sostiene el
   * lock. Si el lock pertenece a un PID que ya no existe (crash previo sin
   * cleanup), lo trata como huerfano y lo recupera -- "recuperacion" real,
   * no solo aspiracional.
   */
  async acquireLock(): Promise<void> {
    await this.ensureDirs();
    const existing = await readJsonIfExists<{ pid: number; startedAt: string }>(this.lockPath);
    if (existing && this._isProcessAlive(existing.pid) && existing.pid !== process.pid) {
      throw new Error(
        `whatsapp_gateway: lock de sesion ya sostenido por PID ${existing.pid} (${this.lockPath}). ` +
          `Un solo proceso puede escribir la sesion a la vez (Fase 4, single-writer).`,
      );
    }
    if (existing && !this._isProcessAlive(existing.pid)) {
      logger.warn(
        { event: "auth_lock_recovered", stale_pid: existing.pid },
        "lock huerfano de un proceso que ya no existe -- recuperado",
      );
    }
    await atomicWriteFile(this.lockPath, JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }));
    this.lockHeld = true;
  }

  async releaseLock(): Promise<void> {
    if (!this.lockHeld) return;
    await rm(this.lockPath, { force: true });
    this.lockHeld = false;
  }

  private _isProcessAlive(pid: number): boolean {
    try {
      process.kill(pid, 0); // no mata nada -- solo prueba existencia (ver docs de Node)
      return true;
    } catch {
      return false;
    }
  }

  async exists(): Promise<boolean> {
    const info = await stat(this.credsPath).catch(() => null);
    return info !== null;
  }

  async getCreds(): Promise<AuthenticationCreds> {
    await this.ensureDirs();
    const existing = await readJsonIfExists<AuthenticationCreds>(this.credsPath);
    return existing ?? initAuthCreds();
  }

  async saveCreds(creds: AuthenticationCreds): Promise<void> {
    await this.ensureDirs();
    await atomicWriteFile(this.credsPath, JSON.stringify(creds, BufferJSON.replacer));
  }

  async getKeys<T extends keyof SignalDataTypeMap>(
    type: T,
    ids: string[],
  ): Promise<{ [id: string]: SignalDataTypeMap[T] }> {
    await this.ensureDirs();
    const result: { [id: string]: SignalDataTypeMap[T] } = {};
    await Promise.all(
      ids.map(async (id) => {
        const filePath = path.join(this.keysDir, keyFileName(type, id));
        let value = await readJsonIfExists<SignalDataTypeMap[T]>(filePath);
        if (type === "app-state-sync-key" && value) {
          value = proto.Message.AppStateSyncKeyData.fromObject(value) as unknown as SignalDataTypeMap[T];
        }
        if (value !== null) {
          result[id] = value;
        }
      }),
    );
    return result;
  }

  async setKeys(data: SignalDataSet): Promise<void> {
    await this.ensureDirs();
    const writes: Promise<void>[] = [];
    for (const category of Object.keys(data) as (keyof SignalDataTypeMap)[]) {
      const entries = data[category];
      if (!entries) continue;
      for (const id of Object.keys(entries)) {
        const value = entries[id];
        const filePath = path.join(this.keysDir, keyFileName(category, id));
        if (value === null || value === undefined) {
          writes.push(rm(filePath, { force: true }));
        } else {
          writes.push(atomicWriteFile(filePath, JSON.stringify(value, BufferJSON.replacer)));
        }
      }
    }
    await Promise.all(writes);
  }

  async removeKeys<T extends keyof SignalDataTypeMap>(type: T, ids: string[]): Promise<void> {
    await Promise.all(ids.map((id) => rm(path.join(this.keysDir, keyFileName(type, id)), { force: true })));
  }

  /**
   * Fase 15 (logout): elimina/inutiliza el auth state real -- nunca deja
   * material criptografico huerfano en disco tras un logout.
   */
  async clear(): Promise<void> {
    await rm(this.credsPath, { force: true });
    const keyFiles = await readdir(this.keysDir).catch(() => [] as string[]);
    await Promise.all(keyFiles.map((f) => rm(path.join(this.keysDir, f), { force: true })));
    await this.releaseLock();
  }
}

/**
 * Adapta FileAuthStateStore a la forma que Baileys espera
 * (`AuthenticationState` + `saveCreds()`), envuelta en
 * `makeCacheableSignalKeyStore` -- misma recomendacion que hace la propia
 * libreria para reducir I/O repetido de las mismas claves dentro de una
 * sesion activa.
 */
export async function toBaileysAuthState(
  store: FileAuthStateStore,
): Promise<{ state: AuthenticationState; saveCreds: () => Promise<void> }> {
  const creds = await store.getCreds();
  return {
    state: {
      creds,
      keys: makeCacheableSignalKeyStore(
        {
          get: (type, ids) => store.getKeys(type, ids),
          set: (data) => store.setKeys(data),
        },
        logger,
      ),
    },
    saveCreds: () => store.saveCreds(creds),
  };
}
