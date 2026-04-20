export interface Persona {
  id?: number;
  tipo: 'FIJOS' | 'RETENES' | 'CUSTODIO' | 'EVENTUALES' | 'SACAFRANCO' | 'SACAVACACIONES' | 'SUPERVISOR ZONAL' | 'SUPERVISOR MOTORIZADO' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
  is_active?: boolean;
}
