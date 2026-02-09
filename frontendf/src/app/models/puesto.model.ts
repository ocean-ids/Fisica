export interface Puesto {
  id: number;
  nombre: string;
  cantidad_guardias: number;
  horas_trabajo: number;
  turno_dia?: boolean;
  turno_noche?: boolean;
  dias?: string[];
  resumen?: string;
  instalacion_id: number;
  descripcion?: string;
  instalacion?: number;
  instalacion_nombre?: string;
  instalacion__provincia?: string;
  instalacion__ciudad?: string;
  turno?: string;
  turno_display?: string;
}
