<template>
  <div class="home">
    <NavBar />
    <HeroSection />
    <FeaturesSection />
    <DemoSection />
    <FooterSection />
  </div>
</template>

<script setup>
import NavBar from '../components/NavBar.vue'
import HeroSection from '../components/HeroSection.vue'
import FeaturesSection from '../components/FeaturesSection.vue'
import DemoSection from '../components/DemoSection.vue'
import FooterSection from '../components/FooterSection.vue'
</script>

<style scoped>
.home {
  min-height: 100vh;
}
</style>

