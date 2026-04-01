export interface PersonalConsola {
  id?: number;
  turno: 'Diurno' | 'Nocturno';
  cedula?: string | null;
  nombres: string;
  apellidos: string;
  is_active: boolean;
}