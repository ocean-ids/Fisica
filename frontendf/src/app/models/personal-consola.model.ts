export interface PersonalConsola {
  id?: number;
  turno: 'Diurno' | 'Nocturno';
  cedula?: string | null;
  nombres: string;
  apellidos: string;
  tipo: 'SUPERVISOR' | 'OPERADOR' | 'OCEAN SECURITY';
  is_active: boolean;
}