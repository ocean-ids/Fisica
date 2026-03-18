export interface City { id: string; nombre: string; }
export interface Province {
  id: string;
  nombre: string;
  region: 'Costa' | 'Sierra' | 'Amazonía' | 'Galápagos';
  ciudades: City[];
}

export const PROVINCIAS: Province[] = [
  // SIERRA
  { id: 'azuay', nombre: 'Azuay', region: 'Sierra', ciudades: [
    { id: 'cuenca', nombre: 'Cuenca' }, { id: 'gualaceo', nombre: 'Gualaceo' }, { id: 'paute', nombre: 'Paute' }
  ] },
  { id: 'bolivar', nombre: 'Bolívar', region: 'Sierra', ciudades: [
    { id: 'guaranda', nombre: 'Guaranda' }
  ] },
  { id: 'canar', nombre: 'Cañar', region: 'Sierra', ciudades: [
    { id: 'azogues', nombre: 'Azogues' }
  ] },
  { id: 'carchi', nombre: 'Carchi', region: 'Sierra', ciudades: [
    { id: 'tulcan', nombre: 'Tulcán' }
  ] },
  { id: 'chimborazo', nombre: 'Chimborazo', region: 'Sierra', ciudades: [
    { id: 'riobamba', nombre: 'Riobamba' }
  ] },
  { id: 'cotopaxi', nombre: 'Cotopaxi', region: 'Sierra', ciudades: [
    { id: 'latacunga', nombre: 'Latacunga' }, { id: 'salcedo', nombre: 'Salcedo' }
  ] },
  { id: 'imbabura', nombre: 'Imbabura', region: 'Sierra', ciudades: [
    { id: 'ibarra', nombre: 'Ibarra' }, { id: 'otavalo', nombre: 'Otavalo' }
  ] },
  { id: 'loja', nombre: 'Loja', region: 'Sierra', ciudades: [
    { id: 'loja', nombre: 'Loja' }, { id: 'catamayo', nombre: 'Catamayo' }
  ] },
  { id: 'pichincha', nombre: 'Pichincha', region: 'Sierra', ciudades: [
    { id: 'quito', nombre: 'Quito' }, { id: 'cayambe', nombre: 'Cayambe' }, { id: 'tumbaco', nombre: 'Tumbaco' }
  ] },
  { id: 'tungurahua', nombre: 'Tungurahua', region: 'Sierra', ciudades: [
    { id: 'ambato', nombre: 'Ambato' }, { id: 'banos', nombre: 'Baños' }
  ] },

  // COSTA
  { id: 'esmeraldas', nombre: 'Esmeraldas', region: 'Costa', ciudades: [
    { id: 'esmeraldas', nombre: 'Esmeraldas' }, { id: 'atacames', nombre: 'Atacames' }, {id: 'quininde', nombre: 'Quinindé' }
  ] },
  { id: 'manabi', nombre: 'Manabí', region: 'Costa', ciudades: [
    { id: 'portoviejo', nombre: 'Portoviejo' }, { id: 'manta', nombre: 'Manta' }, { id: 'chone', nombre: 'Chone' }
  ] },
  { id: 'Guayas', nombre: 'Guayas', region: 'Costa', ciudades: [
    { id: 'guayaquil', nombre: 'Guayaquil' }, { id: 'duran', nombre: 'Durán' }, { id: 'daule', nombre: 'Daule' },
    { id: 'samborondon', nombre: 'Samborondón' }, { id: 'milagro', nombre: 'Milagro' }, { id: 'nobol', nombre: 'Nobol' },
    { id: 'el-triunfo', nombre: 'El Triunfo' }, { id: 'balzar', nombre: 'Bálzar' }, { id: 'posorja', nombre: 'Posorja' }
  ] },
  { id: 'el-oro', nombre: 'El Oro', region: 'Costa', ciudades: [
    { id: 'machala', nombre: 'Machala' }, { id: 'pasaje', nombre: 'Pasaje' }, { id: 'santa-rosa', nombre: 'Santa Rosa' }
  ] },
  { id: 'los-rios', nombre: 'Los Ríos', region: 'Costa', ciudades: [
    { id: 'babahoyo', nombre: 'Babahoyo' }, { id: 'quevedo', nombre: 'Quevedo' }
  ] },
  { id: 'santa-elena', nombre: 'Santa Elena', region: 'Costa', ciudades: [
    { id: 'santa-elena', nombre: 'Santa Elena' }, { id: 'salinas', nombre: 'Salinas' }
  ] },
  { id: 'santo-domingo-de-los-tsachilas', nombre: 'Santo Domingo de los Tsáchilas', region: 'Costa', ciudades: [
    { id: 'santo-domingo', nombre: 'Santo Domingo' }
  ] },

  // AMAZONÍA
  { id: 'napo', nombre: 'Napo', region: 'Amazonía', ciudades: [ { id: 'tena', nombre: 'Tena' } ] },
  { id: 'orellana', nombre: 'Orellana', region: 'Amazonía', ciudades: [ { id: 'coca', nombre: 'Francisco de Orellana (Coca)' } ] },
  { id: 'pastaza', nombre: 'Pastaza', region: 'Amazonía', ciudades: [ { id: 'puyo', nombre: 'Puyo' } ] },
  { id: 'sucumbios', nombre: 'Sucumbíos', region: 'Amazonía', ciudades: [ { id: 'nueva-loja', nombre: 'Nueva Loja (Lago Agrio)' } ] },
  { id: 'morona-santiago', nombre: 'Morona Santiago', region: 'Amazonía', ciudades: [ { id: 'macas', nombre: 'Macas' } ] },
  { id: 'zamora-chinchipe', nombre: 'Zamora Chinchipe', region: 'Amazonía', ciudades: [ { id: 'zamora', nombre: 'Zamora' } ] },

  // GALÁPAGOS
  { id: 'galapagos', nombre: 'Galápagos', region: 'Galápagos', ciudades: [
    { id: 'puerto-baquerizo', nombre: 'Puerto Baquerizo Moreno' }, { id: 'puerto-ayora', nombre: 'Puerto Ayora' }, { id: 'puerto-villamil', nombre: 'Puerto Villamil' }
  ] }
];
