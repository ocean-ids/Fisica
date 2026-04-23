export interface Persona {
  id?: number;
  tipo: 'FIJOS' | 'RETENES' | 'CUSTODIO' | 'EVENTUALES' | 'SACAFRANCO' | 'SACAVACACIONES' | 'SUPERVISOR ZONAL' | 'SUPERVISOR MOTORIZADO' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
  is_active?: boolean;
  provincia?: number | null;
  canton?: number | null;
  provincia_nombre?: string | null;
  canton_nombre?: string | null;
}
