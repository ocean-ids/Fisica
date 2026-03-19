export interface Cliente {
  id?: number;
  codigo?: string;
  ruc?: string;
  razon_social: string;
  nombre_comercial: string;
  size?: 'PEQUENO' | 'MEDIANO' | 'GRANDE' | 'OFICINA';
  fecha_ingreso?: string | null;
  fecha_retiro?: string | null;
}
