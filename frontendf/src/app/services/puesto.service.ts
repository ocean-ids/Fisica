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
        return this.apiService.post('/crear-puesto/', {
            ...puesto,
            turno_dia: puesto.turno_dia ?? false,
            turno_noche: puesto.turno_noche ?? false,
            dias: puesto.dias ?? []
        });
    }


    actualizarPuesto(id: number, puesto: Puesto): Observable<any> {
        return this.apiService.put(`/actualizar-puesto/${id}/`, {
            ...puesto,
            turno_dia: puesto.turno_dia ?? false,
            turno_noche: puesto.turno_noche ?? false,
            dias: puesto.dias ?? []
        });
    }

    eliminarPuesto(id: number): Observable<any>{
        return this.apiService.delete(`/eliminar-puesto/${id}/`);
    }
}