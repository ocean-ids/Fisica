export interface PersonalConsola {
  id?: number;
  fecha: string; // yyyy-mm-dd
  turno: 'Diurno' | 'Nocturno';
  cedula?: string | null;
  nombres: string;
  apellidos: string;
  estado: 'SUPERVISOR' | 'OPERADOR' | 'OCEAN SECURITY';
  is_active: boolean;
}