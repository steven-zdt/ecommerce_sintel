<template>
  <form @submit.prevent="submit">

    <!-- Email -->
    <div class="mb-3">
      <label class="form-label small fw-bold" for="userFormEmail">Email</label>
      <input
        id="userFormEmail"
        v-model="form.email"
        type="email"
        class="form-control"
        :class="{ 'bg-light': mode === 'edit' }"
        required
        maxlength="254"
        :disabled="mode === 'edit'"
        placeholder="usuario@ejemplo.com"
      >
      <div v-if="mode === 'edit'" class="form-text">El email no puede modificarse.</div>
    </div>

    <!-- Nombre + Apellido -->
    <div class="row">
      <div class="col-6 mb-3">
        <label class="form-label small fw-bold" for="userFormFirstName">Nombre</label>
        <input id="userFormFirstName" v-model="form.first_name" type="text" class="form-control" required maxlength="50" placeholder="Nombre">
      </div>
      <div class="col-6 mb-3">
        <label class="form-label small fw-bold" for="userFormLastName">Apellido</label>
        <input id="userFormLastName" v-model="form.last_name" type="text" class="form-control" required maxlength="50" placeholder="Apellido">
      </div>
    </div>

    <!-- Telefono -->
    <div class="mb-3">
      <label class="form-label small fw-bold" for="userFormPhone">Telefono <span class="text-muted fw-normal">(opcional)</span></label>
      <input id="userFormPhone" v-model="form.phone_number" type="tel" class="form-control" maxlength="20" placeholder="+57 300 000 0000">
    </div>

    <!-- Tipo de usuario -->
    <div class="mb-3">
      <label class="form-label small fw-bold">Tipo de Usuario</label>
      <template v-if="mode === 'create'">
        <div class="form-control-plaintext small">
          <span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">Cliente (CUSTOMER)</span>
        </div>
        <div class="form-text">
          Todo usuario nuevo se crea como Cliente. Para técnico, profesional, especialista o
          contratista, el usuario debe solicitar un upgrade desde su panel y ser aprobado en
          Validaciones KYC.
        </div>
      </template>
      <template v-else>
        <div class="form-control-plaintext small">
          <span class="badge" :class="enums.cssClass('user-types', form.user_type)">
            {{ enums.label('user-types', form.user_type, form.user_type) }}
          </span>
        </div>
        <div class="form-text">
          El tipo de usuario no se edita aquí. Cambia únicamente al aprobar una solicitud de
          upgrade en Validaciones KYC.
        </div>
      </template>
    </div>

    <!-- Contrasena (solo crear) -->
    <template v-if="mode === 'create'">
      <div class="mb-3">
        <label class="form-label small fw-bold" for="userFormPassword">Contrasena</label>
        <div class="input-group">
          <input
            id="userFormPassword"
            v-model="form.password"
            :type="showPwd ? 'text' : 'password'"
            class="form-control"
            required
            minlength="8"
            placeholder="Minimo 8 caracteres"
          >
          <button type="button" class="btn btn-outline-secondary" @click="showPwd = !showPwd" tabindex="-1">
            <i :class="showPwd ? 'bi bi-eye-slash' : 'bi bi-eye'"></i>
          </button>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-bold" for="userFormPasswordConfirm">Confirmar Contrasena</label>
        <input
          id="userFormPasswordConfirm"
          v-model="form.password_confirm"
          :type="showPwd ? 'text' : 'password'"
          class="form-control"
          :class="{ 'is-invalid': pwdMismatch, 'is-valid': form.password_confirm && !pwdMismatch }"
          required
          placeholder="Repite la contrasena"
        >
        <div v-if="pwdMismatch" class="invalid-feedback">Las contrasenas no coinciden.</div>
      </div>
    </template>

    <!-- Opciones adicionales (solo editar) -->
    <template v-if="mode === 'edit'">
      <div class="d-flex gap-3 mb-3">
        <div class="form-check form-switch">
          <input v-model="form.is_verified" class="form-check-input" type="checkbox" id="chkVerified">
          <label class="form-check-label small" for="chkVerified">Email verificado</label>
        </div>
      </div>
    </template>

    <!-- Acciones -->
    <div class="d-flex gap-2 mt-4">
      <button
        type="submit"
        class="btn btn-primary flex-grow-1"
        :disabled="loading || (mode === 'create' && pwdMismatch)"
      >
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        {{ mode === 'create' ? 'Crear Usuario' : 'Guardar Cambios' }}
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
        Cancelar
      </button>
    </div>
  </form>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';
import { useUsersAdminStore } from '@/store/usersAdmin';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();
const store = useUsersAdminStore();
const { actionLoading: loading } = storeToRefs(store);
const showPwd = ref(false);

onMounted(() => {
  enums.ensure('user-types');
});

// user_type nunca se envia al backend (ver submit()) -- solo se guarda aqui para
// mostrar el badge de solo lectura en modo edit. Todo usuario nuevo nace CUSTOMER;
// cambiar el tipo de uno existente solo ocurre al aprobar un upgrade en KYC.
const blankForm = () => ({
  email: '',
  first_name: '',
  last_name: '',
  phone_number: '',
  user_type: 'CUSTOMER',
  password: '',
  password_confirm: '',
  is_verified: false,
});

const form = ref(blankForm());

const pwdMismatch = computed(() =>
  props.mode === 'create' && form.value.password_confirm !== '' && form.value.password !== form.value.password_confirm
);

watch(
  () => [props.item, props.mode],
  ([item, m]) => {
    if (item && m === 'edit') {
      form.value = {
        email:          item.email,
        first_name:     item.first_name || item.profile?.first_name || '',
        last_name:      item.last_name  || item.profile?.last_name  || '',
        phone_number:   item.profile?.phone_number || '',
        user_type:      item.profile?.user_type || 'CUSTOMER',
        password:       '',
        password_confirm: '',
        is_verified:    item.is_verified ?? false,
      };
    } else {
      form.value = blankForm();
    }
  },
  { immediate: true }
);

async function submit() {
  if (props.mode === 'create' && form.value.password !== form.value.password_confirm) {
    toast.error('Las contrasenas no coinciden');
    return;
  }
  let res;
  if (props.mode === 'create') {
    res = await store.createUser({
      email:        form.value.email,
      first_name:   form.value.first_name,
      last_name:    form.value.last_name,
      phone_number: form.value.phone_number,
      password:     form.value.password,
      password_confirm: form.value.password_confirm,
    });
  } else {
    res = await store.patchUser(props.item.uuid, {
      first_name:   form.value.first_name,
      last_name:    form.value.last_name,
      phone_number: form.value.phone_number,
      is_verified:  form.value.is_verified,
    });
  }

  if (res.ok) {
    toast.success(props.mode === 'create' ? 'Usuario creado exitosamente' : 'Usuario actualizado exitosamente');
    emit('success');
  } else {
    handleError(res.error, 'Error al guardar el usuario');
  }
}
</script>
