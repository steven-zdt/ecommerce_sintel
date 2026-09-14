import { ref, readonly } from 'vue';

export function useOffcanvas() {
  const show = ref(false);
  const mode = ref('create');        // 'create' | 'edit' | 'detail'
  const selected = ref(null);

  const openCreate = () => {
    // Objeto nuevo (no null) en cada llamada: los formularios hijos usan
    // watch(() => props.item, ...) para poblar/resetear sus campos, y ese
    // watcher solo refire si la referencia cambia. Reutilizar `null` en
    // aperturas consecutivas de "Crear" dejaba datos de la sesion anterior.
    selected.value = {};
    mode.value = 'create';
    show.value = true;
  };

  const openEdit = (item) => {
    selected.value = { ...item }; // Shallow copy to avoid direct mutation
    mode.value = 'edit';
    show.value = true;
  };

  const openDetail = (item) => {
    selected.value = item;
    mode.value = 'detail';
    show.value = true;
  };

  const close = () => {
    show.value = false;
    setTimeout(() => {
        selected.value = null;
    }, 300); // Wait for transition
  };

  // Return as an object that can be safely destructured
  return { 
    show, 
    mode, 
    selected, 
    openCreate, 
    openEdit, 
    openDetail, 
    close 
  };
}

