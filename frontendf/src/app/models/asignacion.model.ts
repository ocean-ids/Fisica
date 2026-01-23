export interface Asignacion{
    id?: number;
    persona: number;
    cliente: number;
    instalacion: number;
    puesto: number;
    horario: number;
    mes: number;
    anio: number;
    fecha_inicio: string;
    fecha_fin?: string;
    rotativo: boolean;
    dias_turno_dia?: number;
    dias_turno_noche?: number;
    dias_franco?: number;
    orden: number;
    estado: string;
    persona_detalle?: string;           
    cliente_detalle?: string;          
    instalacion_detalle?: string;       
    puesto_detalle?: string;            
    horario_detalle?: string; 
}