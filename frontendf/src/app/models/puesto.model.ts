export interface Puesto {
  id: number;
  nombre: string;
  tipo?: string;
  cantidad_puestos: number;
  horas_trabajo?: number;
  dias?: string[];
  horarios?: { dia: number; horas: number; turno?: string }[];
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
