export interface ReporteVacaciones {
  id?: number;
  cliente?: string;
  persona_sale?: string;
  persona_sale_ref?: number | null;
  periodo?: string;
  sacavacaciones?: string;
  sacavacaciones_ref?: number | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
  dias?: number;
  orden?: number;
  created_at?: string;
  updated_at?: string;
}
