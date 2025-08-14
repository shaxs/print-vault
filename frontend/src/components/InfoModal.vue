<script setup>
defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: 'Notification' },
  message: { type: String, required: true },
  isError: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="show" class="modal-overlay" @click="emit('close')">
    <div class="modal-form" @click.stop :class="{ 'error-border': isError }">
      <h3 :class="{ 'error-title': isError }">{{ title }}</h3>
      <p>{{ message }}</p>
      <div class="form-actions">
        <button @click="emit('close')" type="button" class="action-button save-button">OK</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-form {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}
.modal-form.error-border {
  border-left: 5px solid var(--color-red);
}
.modal-form h3 {
  color: var(--color-heading);
  margin-bottom: 20px;
}
.modal-form h3.error-title {
  color: var(--color-red);
}
.modal-form p {
  margin-bottom: 20px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.action-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
</style>
