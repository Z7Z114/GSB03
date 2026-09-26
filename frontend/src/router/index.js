import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: () => import('../views/Home.vue')
    },
    {
        path: '/localization',
        name: 'Localization',
        component: () => import('../views/Localization.vue')
    },
    {
        path: '/processing',
        name: 'Processing',
        component: () => import('../views/Processing.vue')
    },
    {
        path: '/transcripts',
        name: 'Transcripts',
        component: () => import('../views/Transcripts.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
