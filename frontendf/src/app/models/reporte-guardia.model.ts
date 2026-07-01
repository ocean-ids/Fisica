export type SeccionGuardia =
  | 'DOBLADAS' | 'ADICIONALES' | 'ADELANTOS'
  | 'NO_CUBIERTOS' | 'FALTOS' | 'HUECA' | 'APOYO';

export interface ReporteGuardia {
  id?: number;
  fecha: string;
  turno: 'Diurno' | 'Nocturno';
  seccion: SeccionGuardia;
  cliente?: string;
  puesto?: string;
  persona_nombre?: string;
  persona_ref?: number | null;
  reporte_asistencia?: number | null;
  auto?: boolean;
  proviene?: string;
  valor?: number;
  tipo?: string;
  autorizacion?: string;
  motivo?: string;
  fecha_evento?: string | null;
  orden?: number;
  created_at?: string;
  update_at?: string;
}
