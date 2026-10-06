export interface ReporteAsistenciaRow {
  asignacion_id?: number | null;
  sacafranco_fila_id?: number | null;
  codigo?: string | null;
  cliente?: string;
  instalacion_nombre?: string;
  puesto?: string;
  puesto_tipo?: string;
  horario?: string;
  turno?: string;
  nombre_apellidos?: string;
  apellidos_txt?: string;     // apellidos de la persona que se muestra (para verlos arriba)
  nombres_txt?: string;       // nombres de la persona que se muestra (para verlos abajo)
  reemplazo_id?: number | null;
  reemplazo?: string;
  estado_asistencia?: 'ASISTIO' | 'FALTO' | '' | null;
  estado?: string;
  descripcion?: string | null;
  modificado_por?: string;
  row_color?: string | null;
  hueca?: boolean;
  hueca_motivo?: string;
  es_hueca?: boolean;
  persona_cobertura_id?: number | null;
  // Movimiento interno: el guardia mostrado es titular de otro puesto y cubrió aquí ese día.
  movimiento_interno?: boolean;
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
  turno?: string | null;     // filtro desde el que se guarda (para la V de 24 horas en la guardia)
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
