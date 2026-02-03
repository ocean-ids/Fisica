export interface Persona {
  id?: number;
  tipo: 'SUPERVISOR' | 'FIJO' | 'FRANCO' | 'SACAFRANCO' | 'EVENTUAL' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
}
