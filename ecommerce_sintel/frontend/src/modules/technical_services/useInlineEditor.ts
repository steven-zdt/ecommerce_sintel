import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue';

/**
 * Composable para gestionar la lógica de un editor inline.
 * @param onSave - La función asíncrona que se ejecuta al guardar.
 */
export function useInlineEditor(onSave: (value: any) => Promise<void>) {
  const isEditing = ref(false);
  const loading = ref(false);
  const error = ref('');

  const editorRef = ref<HTMLElement | null>(null);
  const inputRef = ref<HTMLElement | null>(null);

  // Cerrar al hacer clic fuera (sin @vueuse/core: no esta instalado en el proyecto)
  const handleClickOutside = (event: MouseEvent) => {
    if (isEditing.value && editorRef.value && !editorRef.value.contains(event.target as Node)) {
      cancel();
    }
  };
  onMounted(() => document.addEventListener('mousedown', handleClickOutside));
  onBeforeUnmount(() => document.removeEventListener('mousedown', handleClickOutside));

  const startEditing = async () => {
    isEditing.value = true;
    await nextTick();
    if (inputRef.value && 'focus' in inputRef.value) {
      (inputRef.value as HTMLElement).focus();
    }
    if (inputRef.value && 'select' in inputRef.value) {
        (inputRef.value as HTMLInputElement).select();
    }
  };

  const save = async (value: any) => {
    if (!isEditing.value) return;
    loading.value = true;
    error.value = '';
    try {
      await onSave(value);
      isEditing.value = false;
    } catch (e: any) {
      error.value = e.message || 'Error al guardar.';
      // No cerramos el editor para que el usuario pueda corregir.
    } finally {
      loading.value = false;
    }
  };

  const cancel = () => {
    isEditing.value = false;
    error.value = '';
  };

  return {
    isEditing,
    loading,
    error,
    editorRef,
    inputRef,
    startEditing,
    save,
    cancel,
  };
}