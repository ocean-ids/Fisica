export interface Asignacion{
    id?: number;
    persona: number;
    instalacion: number;
    puesto: number;
    horario:number;
    mes: number;
    anio: number;
    fecha_inicio: string;
    fecha_fin?: string;
    rotativo: boolean;
    orden: number;
    estado: string;
    persona_nombre?: string;           
    cliente_nombre?: string;          
    instalacion_nombre?: string;       
    puesto_nombre?: string;            
    horario_denominativo?: string; 
}

