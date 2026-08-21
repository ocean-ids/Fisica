export interface ReporteAsistenciaRow {
  asignacion_id?: number | null;
  codigo?: string | null;
  cliente?: string;
  puesto?: string;
  puesto_tipo?: string;
  horario?: string;
  nombre_apellidos?: string;
  reemplazo_id?: number | null;
  reemplazo?: string;
  estado_asistencia?: 'ASISTIO' | 'FALTO' | '' | null;
  estado?: string;
  descripcion?: string | null;
  modificado_por?: string;
  row_color?: string | null;
  hueca?: boolean;
  hueca_motivo?: string;
  modificado_en?: string | null;
  zona_titulo?: string;
  provincia?: string;
}

export interface UpdateReporteAsistenciaPayload {
  codigo?: string | null;
  estado_asistencia?: 'ASISTIO' | 'FALTO' | null;
  estado?: string | null;
  reemplazo_id?: number | null;
  descripcion?: string | null;
  row_color?: string | null;
  hueca?: boolean;
  hueca_motivo?: string | null;
  fecha?: string | null;
}

export interface ReporteAsistenciaHistorialItem {
  fecha_reporte?: string | null;
  usuario?: string;
  codigo?: string;
  estado_asistencia?: 'ASISTIO' | 'FALTO' | '' | null;
  estado?: string;
  reemplazo?: string;
  descripcion?: string;
  row_color?: string;
  creado_en?: string | null;
}

export interface ResumenAsistencia {
  total: number;
  asistencias: number;
  faltas: number;
  por_zona?: ResumenAsistenciaZona[];
}

export interface ResumenAsistenciaZona {
  zona: string;
  total: number;
  asistencias: number;
  faltas: number;
}

export interface ReporteAsistenciaListResponse {
  results: ReporteAsistenciaRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  zona?: string | null;
}
