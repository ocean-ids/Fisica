import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Injectable } from '@angular/core';
import { AsignacionSemanal } from '../models/asignacion-calendario';

@Injectable({
  providedIn: 'root'
})
export class AsignacionCalendarioService {
  constructor(private apiService: ApiService){}

  obtenerAsignacionesCalendario(params?: any): Observable<any>{
    return this.apiService.get<any>('/asignacion-semanal/', params);
  }

  obtenerSemanas(mes: number, anio: number): Observable<any>{
    return this.apiService.get<any>('/semanas/', { mes, anio });
  }

  crearAsignacionCalendario(asignacion: AsignacionSemanal): Observable<any>{
    return this.apiService.post<any>('/asignacion-semanal/guardar/', asignacion);
  }

}
