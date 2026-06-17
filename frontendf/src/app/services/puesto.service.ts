import { Injectable } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { Observable, throwError } from 'rxjs';
import { ApiService } from './api.service';
import { Puesto } from '../models/puesto.model'; // Actualizado para usar el archivo correcto

@Injectable({
  providedIn: 'root'
})
export class PuestoService {
    constructor(private apiService: ApiService){}

    getPuestos(): Observable<Puesto[]>{
        return this.apiService.get<Puesto[]>('/puestos/');
    }

    getPuestosPorInstalacion(instalacionId: number): Observable<Puesto[]>{
        return this.apiService.get<Puesto[]>(`/puestos/instalacion/${instalacionId}/`);
    }

    getPuestosPorCliente(clienteId: number): Observable<Puesto[]>{
        return this.apiService.get<Puesto[]>(`/puestos/cliente/${clienteId}/`);
    }

    crearPuesto(puesto: Puesto): Observable<any> {
        const payload: any = { ...puesto };
        if (puesto.horarios) payload.horarios = puesto.horarios;
        else {
            payload.dias = puesto.dias ?? [];
            payload.turno = puesto.turno;
        }
        return this.apiService.post('/crear-puesto/', payload);
    }

    actualizarPuesto(id: number, puesto: Puesto): Observable<any> {
        const payload: any = { ...puesto };
        if (puesto.horarios) payload.horarios = puesto.horarios;
        else {
            payload.dias = puesto.dias ?? [];
            payload.turno = puesto.turno;
        }
        return this.apiService.put(`/actualizar-puesto/${id}/`, payload);
    }

    eliminarPuesto(id: number): Observable<any>{
        return this.apiService.delete(`/eliminar-puesto/${id}/`);
    }

    getSecuenciaHorario(id: number): Observable<{ secuencia: string; resumen: string }> {
        return this.apiService.get<{ secuencia: string; resumen: string }>(`/puestos/${id}/secuencia-horario/`);
    }

    importPuestosAsignaciones(file: File, clienteId?: number): Observable<any> {
        const formData = new FormData();
        formData.append('file', file);
        const endpoint = clienteId
            ? `/importar-puestos-asignaciones/?cliente_id=${clienteId}`
            : '/importar-puestos-asignaciones/';
        return this.apiService.post<any>(endpoint, formData);
    }
}