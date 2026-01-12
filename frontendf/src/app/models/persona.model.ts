export interface Persona {
  id?: number;
  tipo: 'SUPERVISOR' | 'FIJO' | 'FRANCO' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
}
