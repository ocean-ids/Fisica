import { Component, OnInit } from '@angular/core';
import { AsignacionCalendario } from '../../models/asignacion-calendario';
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';

@Component({
  selector: 'app-asignacion-calendario',
  imports: [],
  templateUrl: './asignacion-calendario.component.html',
  styleUrl: './asignacion-calendario.component.css'
})
export class AsignacionCalendarioComponent implements OnInit{
  asignaciones: AsignacionCalendario[] = [];
  nueva: AsignacionCalendario = { asignacion: 0, fecha: '', turno: '', dia_numero: undefined };
  page= 1;
  pageSize = 10;
  total = 0;

  constructor(private asignacionCalendarioService: AsignacionCalendarioService){}

  ngOnInit(): void {
    this.cargarAsignaciones();
  }

  cargarAsignaciones(){
    this.asignacionCalendarioService.obtenerAsignacionesCalendario({page: 1, page_size:10})
      .subscribe(res => {
        this.asignaciones = res.results;
      });
  }

  crearAsignacion(){
    this.asignacionCalendarioService.crearAsignacionCalendario(this.nueva)
    .subscribe(res => {
      this.cargarAsignaciones();
      this.nueva = {asignacion: 0,
        fecha:'',turno:'', dia_numero: undefined
      };
    })
  }

  siguientePagina(){
    if ((this.page * this.pageSize) < this.total){
      this.page++;
      this.cargarAsignaciones();
    }
  }

  anteriorPagina(){
    if (this.page > 1){
      this.page--;
      this.cargarAsignaciones();
    }
  }
  

}
