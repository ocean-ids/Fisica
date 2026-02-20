export interface Horario {
    id?: number;
    hora_ingreso: string;
    hora_salida: string;
    patron_id?: number | null;
    patronHorario?: {
        id: number;
        codigo: string;
        secuencia: string[];
    } | null;
}