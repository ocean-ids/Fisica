export interface Instalacion {
  id?: number;
  codigo?: string;
  cliente?: number;
  cliente_id?: number;
  provincia: string;
  ciudad: string;
  nombre?: string;
  direccion?: string;
  nombre_cliente?: string;
  zonas?: { id: number; titulo: string }[];
  nominativo_zona?: string;
}
