// Registro de horas trabajadas por un EVENTUAL (módulo Eventuales).
export interface HorasEventual {
  id?: number;
  fecha: string;              // YYYY-MM-DD (día elegido en la pantalla del módulo)
  persona_id: number;
  persona?: string;           // "APELLIDOS NOMBRES"
  cedula?: string;
  banco?: string;             // solo lectura (sale de los datos de la persona)
  cliente_id: number;
  cliente?: string;
  instalacion_id: number;
  instalacion?: string;
  puesto_id?: number | null;
  puesto?: string;
  horas: number;              // horas trabajadas (enteras)
  horas_adicionales?: number;
  valor_calculado?: number;   // tarifa "Eventuales" del tramo (horas + adicionales)
}

// Datos para los selectores del formulario.
export interface CatalogoHorasEventual {
  clientes: Array<{ id: number; nombre: string }>;
  instalaciones: Array<{ id: number; nombre: string; cliente_id: number }>;
  puestos: Array<{ id: number; nombre: string; instalacion_id: number }>;
  eventuales: Array<{ id: number; nombre: string; cedula: string; banco: string }>;
  tarifas: Array<{ horas_min: number; horas_max: number; valor: number }>;   // tarifa "Eventuales"
}
