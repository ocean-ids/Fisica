export interface Persona {
  id?: number;
  tipo: 'FIJOS' | 'RETEN' | 'CUSTODIO' | 'EVENTUAL' | 'SACAFRANCO' | 'SACAVACACIONES' | 'SUPERVISOR ZONAL' | 'SUPERVISOR EVENTUAL' | 'SUPERVISOR MOTORIZADO' | 'SUPERVISOR DE ACOMPAÑAMIENTO' | 'OPERADOR CENTRO CONTROL' | 'SUPERVISOR CENTRO CONTROL' | null;
  nombres: string;
  apellidos: string;
  cedula: string;
  is_active?: boolean;
  provincia?: number | null;
  canton?: number | null;
  provincia_nombre?: string | null;
  canton_nombre?: string | null;

  foto?: string | null;
  codigo_erp?: string;
  cargo?: string;
  sexo?: string;
  estado_civil?: string;
  fecha_nacimiento?: string | null;
  lugar_nacimiento?: string;
  nacionalidad?: string;
  telefono?: string;
  correo_personal?: string;
  direccion?: string;
  parroquia?: string;
  fecha_ingreso?: string | null;
  fecha_salida?: string | null;
  seccion?: string;
  departamento?: string;
  unidad_negocio?: string;
  tipo_empleado?: string;
  cliente?: number | null;
  cliente_nombre?: string | null;

}
