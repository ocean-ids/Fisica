export interface Asignacion{
    id?: number;
    persona: number;
    cliente: number;
    instalacion: number;
    puesto: number;
    horario: number;
    mes: number;
    anio: number;
    rotativo: boolean;
    dias_franco?: number;
    estado: string;
    persona_detalle?: any;           
    cliente_detalle?: any; 
    clienteCodigo: string;       
    instalacion_detalle?: any;       
    puesto_detalle?: any;            
    horario_detalle?: any; 
    
}