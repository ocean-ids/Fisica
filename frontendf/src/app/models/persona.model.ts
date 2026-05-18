export interface Persona {
  id?: number;
  tipo: 'FIJOS' | 'RETEN' | 'CUSTODIO' | 'EVENTUAL' | 'SACAFRANCO' | 'SACAVACACIONES' | 'SUPERVISOR ZONAL' | 'SUPERVISOR EVENTUAL' | 'SUPERVISOR MOTORIZADO' | 'SUPERVISOR DE ACOMPAÑAMIENTO' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
  is_active?: boolean;
  provincia?: number | null;
  canton?: number | null;
  provincia_nombre?: string | null;
  canton_nombre?: string | null;
}
