import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Horario } from '../models/horario.models';



@Injectable({
  providedIn: 'root'
})
export class HorarioService {

  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) { }

  private getHeaders(): HttpHeaders{
    const token = localStorage.getItem('access_token');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  obtenerHorarios(): Observable<Horario[]>{
    return this.http.get<Horario[]>(`${this.apiUrl}/horarios/`,{
      headers: this.getHeaders()
    });
  }

  crearHorario(horario: Horario): Observable<any>{
    return this.http.post(`${this.apiUrl}/crear-horario/`, horario,{
      headers: this.getHeaders()
    });
  }

  actualizarHorario(id: number, horario: Horario): Observable<any>{
    return this.http.put(`${this.apiUrl}/actualizar-horario/${id}/`, horario, {
      headers: this.getHeaders()
    });
  }

  eliminarHorario(id:number): Observable<any>{
    return this.http.delete(`${this.apiUrl}/eliminar-horario/${id}/`,{
      headers: this.getHeaders()
    });
  }

  obtenerPatrones(): Observable<any[]>{
    return this.http.get<any[]>(`${this.apiUrl}/patrones/`, {
      headers: this.getHeaders()
    });
  }

  crearPatron(payload: any): Observable<any>{
    return this.http.post(`${this.apiUrl}/crear-patron/`, payload, {
      headers: this.getHeaders()
    });
  }

  actualizarPatron(id: number, payload: any): Observable<any>{
    return this.http.put(`${this.apiUrl}/actualizar-patron/${id}/`, payload, {
      headers: this.getHeaders()
    });
  }

  eliminarPatron(id: number): Observable<any>{
    return this.http.delete(`${this.apiUrl}/eliminar-patron/${id}/`, {
      headers: this.getHeaders()
    });
  }

}
