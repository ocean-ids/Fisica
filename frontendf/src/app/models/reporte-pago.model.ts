export interface ReportePago {
  id?: number;
  fecha: string;
  turno: 'Diurno' | 'Nocturno';
  seccion?: string;
  reporte_guardia_ref?: number | null;
  persona_ref?: number | null;
  cliente?: string;
  puesto?: string;
  persona_nombre?: string;
  cedula?: string;
  banco?: string;
  tipo_cuenta?: string;
  numero_cuenta?: string;
  tipo_servicio?: string;
  horas?: number | null;
  valor_calculado?: number;
  valor_total?: number | null;
  referencia?: string;
  auto?: boolean;
  orden?: number;
}

export interface TarifaPago {
  id?: number;
  tipo_servicio: string;
  horas_min: number;
  horas_max: number;
  valor: number;
  orden?: number;
}

export interface ResumenMensualPago {
  mes: number;
  anio: number;
  total_general: number;
  por_tipo_servicio: Array<{ tipo_servicio: string; total: number }>;
  por_persona: Array<{ persona_id: number | null; persona_nombre: string; cedula: string; total: number }>;
}
