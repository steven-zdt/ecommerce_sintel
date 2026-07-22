import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// Estilos globales (opcional, ya que usamos CoreUI/Bootstrap en base.html)
// import './style.css'

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.mount('#shop-spa-root');
