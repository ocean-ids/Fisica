import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Injectable } from '@angular/core';
import { AsignacionCalendario } from '../models/asignacion-calendario';

@Injectable({
  providedIn: 'root'
})
export class AsignacionCalendarioService {
  constructor(private apiService: ApiService){}

  obtenerAsignacionesCalendario(params?: any): Observable<any>{
    return this.apiService.get<any>('/asignacion-calendario/', params);
  }

  crearAsignacionCalendario(asignacion: AsignacionCalendario): Observable<any>{
    return this.apiService.post<any>('/asignacion-calendario/crear/', asignacion);
  }
}
