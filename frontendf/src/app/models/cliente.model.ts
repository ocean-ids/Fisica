export interface Cliente {
  id?: number;
  ruc?: string;
  razon_social: string;
  nombre_comercial: string;
  size?: 'PEQUENO' | 'MEDIANO' | 'GRANDE' | 'OFICINA';
  fecha_ingreso?: string | null;
  fecha_retiro?: string | null;
  instalaciones_count?: number;   // instalaciones abiertas (lo manda la lista de clientes)
}
