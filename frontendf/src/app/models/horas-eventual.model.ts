// Registro de horas trabajadas por un EVENTUAL (módulo Eventuales).
export interface HorasEventual {
  id?: number;
  fecha: string;              // YYYY-MM-DD (día elegido en la pantalla del módulo)
  persona_id: number;
  persona?: string;           // "APELLIDOS NOMBRES"
  cedula?: string;
  banco?: string;             // solo lectura (sale de los datos de la persona)
  banco_codigo?: string;      // código del banco (10 PICHINCHA, 17 GUAYAQUIL, 36 PRODUBANCO)
  tipo_cuenta?: string;
  numero_cuenta?: string;
  // Cliente / instalación / puesto: de la lista (id) o escritos a mano (texto, solo en este registro).
  cliente_id?: number | null;
  cliente_texto?: string;
  cliente?: string;
  instalacion_id?: number | null;
  instalacion_texto?: string;
  instalacion?: string;
  puesto_id?: number | null;
  puesto_texto?: string;
  puesto?: string;
  cliente_libre?: boolean;
  instalacion_libre?: boolean;
  puesto_libre?: boolean;
  horas_solicitadas?: number; // las que pidió el cliente
  horas: number;              // horas trabajadas (enteras)
  horas_adicionales?: number; // trabajadas - solicitadas (lo calcula el servidor)
  rango_horas?: string;       // tramo de la tarifa usado, ej. "10-12 h"
  tarifa_id?: number | null;  // (al guardar) tramo elegido en el formulario
  bonificacion?: number | null; // bono opcional
  valor_calculado?: number;   // por defecto: valor del rango + bonificación
  valor_manual?: boolean;     // true = se escribió a mano
  // Auditoría (solo lectura)
  creado_por?: string;
  creado_en?: string | null;
  modificado_por?: string;    // último que lo guardó
  modificado_en?: string | null;
}

// Una versión del registro en su historial (quién, cuándo, valores y qué cambió).
export interface HorasEventualHistorialItem {
  id: number;
  accion: 'CREADO' | 'MODIFICADO';
  accion_label: string;
  usuario: string;
  fecha_hora: string | null;
  fecha_servicio: string | null;
  persona: string;
  cliente: string;
  instalacion: string;
  puesto: string;
  horas_solicitadas: number | null;
  horas: number | null;
  horas_adicionales: number | null;
  rango_horas: string;
  valor_calculado: number | null;
  bonificacion: number | null;
  cambios: string[];          // etiquetas de los campos que cambiaron respecto a la versión anterior
}

// Datos para los selectores del formulario.
export interface CatalogoHorasEventual {
  clientes: Array<{ id: number; nombre: string }>;
  instalaciones: Array<{ id: number; nombre: string; cliente_id: number }>;
  puestos: Array<{ id: number; nombre: string; instalacion_id: number }>;
  eventuales: Array<{ id: number; nombre: string; cedula: string; banco: string; tipo?: string }>;
  tarifas: Array<{ id: number; horas_min: number; horas_max: number; valor: number }>;   // tarifa "Eventuales"
}
