const AiAssistantView = () => import('@/modules/ai-assistant/AiAssistantView.vue');

export const adminAiRoutes = [
  { path: 'asistente', name: 'ai-assistant', component: AiAssistantView },
];
