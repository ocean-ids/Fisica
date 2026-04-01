export interface ConsolidadoRow {
  consolidado_id?: number;
  fecha?: string;
  turno?: 'Diurno' | 'Nocturno';
  tipo?: 'CONSOLa' | 'GUARDIA';
  referencia_id?: number;
  proyecto?: string;
  puesto?: string;
  cedula?: string | null;
  apellidos?: string;
  nombres?: string;
  estado?: string;
  observacion?: string;
}
