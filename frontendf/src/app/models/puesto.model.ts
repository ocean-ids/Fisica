export interface Puesto {
  id: number;
  nombre: string;
  horas_trabajo: number;
  instalacion_id: number;
  cantidad_guardias: number;
  descripcion?: string;
  instalacion?: number;
  instalacion_nombre?: string;
  instalacion__provincia?: string;
  instalacion__ciudad?: string;
}
