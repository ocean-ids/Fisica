import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { HttpClient } from '@angular/common/http';
import { Asignacion } from '../models/asignacion.model';

@Injectable({
  providedIn: 'root'
})
export class AsignacionService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient){}

  obtenerAsignaciones(mes: number, anio:number): Observable<Asignacion[]> {
    return this.http.get<Asignacion[]>(`${this.apiUrl}/asignaciones/${mes}/${anio}/`);
  }

  crearAsignacion(asignacion: Asignacion): Observable<Asignacion> {
    return this.http.post<Asignacion>(`${this.apiUrl}/asignar-servicio/`, asignacion);
  }

  actualizarAsignacion(id: number, asignacion: Asignacion): Observable<Asignacion> {
    return this.http.put<Asignacion>(`${this.apiUrl}/editar-servicio/${id}/`, asignacion);
  }

  eliminarAsignacion(id: number): Observable<any>{
    return this.http.delete<any>(`${this.apiUrl}/eliminar-asignacion/${id}/`);
  }

  guardarOrden(ordenes: {id: number, orden: number}[]): Observable<any>{
    return this.http.post<any>(`${this.apiUrl}/guardar-orden-asignacion/`, {ordenes});
  }
  
}
