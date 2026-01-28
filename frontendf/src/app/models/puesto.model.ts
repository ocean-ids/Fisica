export interface Puesto {
  id: number;
  nombre: string;
  cantidad_guardias: number;
  horas_trabajo: number;
  sistema: string;
  descripcion_sistema?: string;
  instalacion_id: number;
  descripcion?: string;
  instalacion?: number;
  instalacion_nombre?: string;
  instalacion__provincia?: string;
  instalacion__ciudad?: string;
}
