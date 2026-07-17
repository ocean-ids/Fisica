export const environment = {
  production: false,
  // Relativo: las llamadas van al mismo origen (el túnel) y ng serve las
  // reenvía al backend local via proxy.conf.json. Así compartir solo el
  // puerto 4200 funciona con backend + base.
  apiUrl: '/api'
};
