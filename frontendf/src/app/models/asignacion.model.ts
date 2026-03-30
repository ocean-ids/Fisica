import { Persona } from './persona.model';

export interface Asignacion{
    id?: number;
    persona: number;
    cliente: number;
    instalacion: number;
    puesto: number;
    horario: number;
    mes: number;
    anio: number;
    dias_franco?: number;
    estado: string;
    persona_detalle?: Persona | null;
    cliente_detalle?: any; 
    instalacionCodigo?: string;       
    instalacion_detalle?: any;       
    puesto_detalle?: any;            
    horario_detalle?: any; 
    recurring?: boolean;
    start_date?: string | null;
    end_date?: string | null;
    patronAsignacion?: number;
    agregar_sacafranco?: boolean;
    sacafranco_grupo?: number | null;
    orden?: number;
    
}

export interface SacafrancoFila {
    id?: number;
    mes: number;
    anio: number;
    orden?: number;
    persona: number;
    persona_detalle?: Persona | null;
}

export interface PatronAsignacion{
    id?: number;
    codigo: string;
    secuencia: string[];
}