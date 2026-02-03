import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { AsignacionSemanal } from '../../models/asignacion-calendario';
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';
import { PuestoService } from '../../services/puesto.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-asignacion-calendario',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './asignacion-calendario.component.html',
  styleUrl: './asignacion-calendario.component.css'
})
export class AsignacionCalendarioComponent implements OnInit{
  weekStart: string = '';
  weekDays: Array<{short:string, name:string, date:string, dayNum:number}> = [];
  rows: any[] = [];
  loading = false;
  

  constructor(private asignacionCalendarioService: AsignacionCalendarioService, private puestoService: PuestoService){}

  ngOnInit(): void {
    this.weekStart = this.computeCurrentMonday();
    this.loadWeek();
  }

  computeCurrentMonday(): string{
    const today = new Date();
    const day = today.getDay(); // 0 Domingo .. 6 Sab
    const diff = (day === 0 ? -6 : 1) - day; // mover a lunes
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);
    return monday.toISOString().slice(0,10);
  }

  loadWeek(){
    // Recompute display labels for the current week
    this.computeWeekDays();
    this.loading = true;
    this.asignacionCalendarioService.obtenerAsignacionesCalendario({week_start: this.weekStart})
      .subscribe(res => {
        if (Array.isArray(res)) {
          this.rows = res;
        } else if (res && Array.isArray(res.results)) {
          this.rows = res.results;
        } else {
          this.rows = [];
        }

        // Si no hay filas guardadas, cargar puestos para mostrar filas editables
        if((!this.rows || this.rows.length === 0)){
          this.puestoService.getPuestos().subscribe(puestos => {
            this.rows = puestos.map(p => ({ puesto: p.id, puesto_detalle: p, mon: '', tue: '', wed: '', thu: '', fri: '', sat: '', sun: '' }));
          });
        }
          this.loading = false;
          // Notificar a quien escuche que la semana actual cambió
          try { this.weekStartChange.emit(this.weekStart); } catch(e){}
      }, ()=> this.loading = false);
  }

        @Output() weekStartChange: EventEmitter<string> = new EventEmitter<string>();

  saveRow(row: any){
    const payload: AsignacionSemanal = {
      puesto: row.puesto || (row.puesto_detalle && row.puesto_detalle.id),
      week_start: this.weekStart,
      mon: row.mon || '',
      tue: row.tue || '',
      wed: row.wed || '',
      thu: row.thu || '',
      fri: row.fri || '',
      sat: row.sat || '',
      sun: row.sun || ''
    };
    this.asignacionCalendarioService.crearAsignacionCalendario(payload)
      .subscribe(() => this.loadWeek());
  }
  

  onCellChange(row: any, day: string, value: any){
    const v = value ? String(value).toUpperCase().slice(0,4) : '';
    row[day] = v;
  }

  getCellClass(value: string){
    if(!value) return '';
    const v = value.toString().toUpperCase();
    if(v.startsWith('F')) return 'cell-franco';
    if(v.startsWith('D')) return 'cell-dia';
    if(v.startsWith('N')) return 'cell-noche';
    if(v.startsWith('DS') || v.startsWith('NS')) return 'cell-desc';
    if(v.startsWith('MA') || v.startsWith('MI')) return 'cell-daycode';
    return '';
  }
  
  computeWeekDays(): void {
    this.weekDays = [];
    if (!this.weekStart) return;
    const base = new Date(this.weekStart);
    // Use the actual weekday names based on the base date; do not assume Monday
    const shortNames = ['Do','Lu','Ma','Mi','Ju','Vi','Sá'];
    const fullNames = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
    for (let i = 0; i < 7; i++){
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const wd = d.getDay(); // 0=Dom .. 6=Sab
      this.weekDays.push({
        short: shortNames[wd],
        name: fullNames[wd],
        date: d.toISOString().slice(0,10),
        dayNum: d.getDate()
      });
    }
  }

}
