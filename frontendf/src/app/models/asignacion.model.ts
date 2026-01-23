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
    persona_detalle?: any;           
    cliente_detalle?: any;          
    instalacion_detalle?: any;       
    puesto_detalle?: any;            
    horario_detalle?: any; 
}