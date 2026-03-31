export interface ReporteAsistenciaRow {
  asignacion_id?: number | null;
  codigo?: string | null;
  cliente?: string;
  puesto?: string;
  horario?: string;
  nombre_apellidos?: string;
  reemplazo_id?: number | null;
  reemplazo?: string;
  estado?: string;
  descripcion?: string | null;
  modificado_por?: string;
  row_color?: string | null;
  modificado_en?: string | null;
  zona_titulo?: string;
  provincia?: string;
}

export interface UpdateReporteAsistenciaPayload {
  codigo?: string | null;
  estado?: string | null;
  reemplazo_id?: number | null;
  descripcion?: string | null;
  row_color?: string | null;
  fecha?: string | null;
}

export interface ReporteAsistenciaHistorialItem {
  fecha_reporte?: string | null;
  usuario?: string;
  codigo?: string;
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
