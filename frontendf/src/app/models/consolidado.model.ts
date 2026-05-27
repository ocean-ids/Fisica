export interface ConsolidadoRow {
  consolidado_id?: number;
  fecha?: string;
  turno?: 'Diurno' | 'Nocturno';
  tipo?: 'CONSOLa' | 'GUARDIA';
  referencia_id?: number;
  nominativo?: string;
  proyecto?: string;
  puesto?: string;
  cedula?: string | null;
  apellidos?: string;
  nombres?: string;
  estado?: string;
  observacion?: string;
  zona?: string;
}

export interface ConsolidadoResumenManual {
  faltas: number;
  huecas: number;
  apoyos: number;
  capacitacion: number;
  apertura_puesto: number;
  servicios_temporales: number;
  servicios_adicionales: number;
  aprendiendo_consignas: number;
  total: number;
}

export interface ConsolidadoResumenEstado {
  dobla: number;
  franco_trabajados: number;
  unidades_eventuales: number;
  adelanto_turno: number;
  reten: number;
  unidades_adicionales: number;
  custodio: number;
  total: number;
}

export interface ConsolidadoResumenResponse {
  manual: ConsolidadoResumenManual | null;
  estado_agentes: ConsolidadoResumenEstado;
}
