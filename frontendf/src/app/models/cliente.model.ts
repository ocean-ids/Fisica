export interface Cliente {
  id?: number;
  ruc?: string;
  razon_social: string;
  nombre_comercial: string;
  size?: 'PEQUEÑO' | 'MEDIANO' | 'GRANDE';
}
