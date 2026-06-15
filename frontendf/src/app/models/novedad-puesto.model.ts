export type TurnoNovedad = 'Diurno' | 'Nocturno';

export type TipoNovedad =
  | 'APERTURA'
  | 'MODIFICACION'
  | 'CIERRE'
  | 'INCREMENTO'
  | 'MODIFICACION INCREMENTO';

export interface NovedadPuesto {
  id?: number;
  puesto?: number | null;
  instalacion?: number | null;
  fecha: string;            // YYYY-MM-DD
  turno: TurnoNovedad;
  cliente_denominativo: string;
  sector: string;
  novedad: TipoNovedad | string;
  tipo: string;
  horario: string;
  solicitado_por: string;
  observacion: string;
  creado_en?: string;
}
