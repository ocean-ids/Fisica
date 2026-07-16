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
