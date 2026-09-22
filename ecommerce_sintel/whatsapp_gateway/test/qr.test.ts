import "./setup.js";
import assert from "node:assert/strict";
import { test } from "node:test";

import { encodeQrAsDataUrl } from "../src/qr.js";

test("encodeQrAsDataUrl produce un data URL PNG real, nunca el string crudo", async () => {
  const dataUrl = await encodeQrAsDataUrl("2@fake-baileys-ref-string,fake-key==,fake-id=");
  assert.match(dataUrl, /^data:image\/png;base64,/);
  assert.ok(dataUrl.length > 100, "un QR real codificado no deberia ser un string minusculo");
});
