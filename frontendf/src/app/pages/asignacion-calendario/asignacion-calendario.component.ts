import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { AsignacionSemanal } from '../../models/asignacion-calendario';
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';
import { PuestoService } from '../../services/puesto.service';
import { AsignacionService } from '../../services/asignacion.service';
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
  weeks: string[] = [];
  currentWeekIndex: number = 0;
  weekDays: Array<{short:string, name:string, date:string, dayNum:number}> = [];
  rows: any[] = [];
  loading = false;
  @Input() allowCreateEmptyRows: boolean = false;
  

  constructor(
    private asignacionCalendarioService: AsignacionCalendarioService,
    private puestoService: PuestoService,
    private asignacionService: AsignacionService
  ){}

  ngOnInit(): void {
    this.weekStart = this.computeCurrentMonthStart();
    const base = new Date(this.weekStart);
    this.loadWeeksForMonth(base.getMonth()+1, base.getFullYear());
  }

  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }


  computeCurrentMonthStart(): string{
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}-01`;
  }

  loadWeek(){
  
    this.computeWeekDays();
    this.loading = true;
    this.asignacionCalendarioService.obtenerAsignacionesCalendario({week_start: this.weekStart, auto_create: true})
      .subscribe({
        next: (res: any) => {
        if (Array.isArray(res)) {
          this.rows = res;
        } else if (res && Array.isArray(res.results)) {
          this.rows = res.results;
        } else {
          this.rows = [];
        }

        
        if((!this.rows || this.rows.length === 0)){
          const parts = (this.weekStart||'').split('-').map(Number);
          const base = (parts.length===3) ? new Date(parts[0], parts[1]-1, parts[2]) : new Date();
          const mes = base.getMonth() + 1;
          const anio = base.getFullYear();
          // Si no hay filas semanales en la base, solo mostramos filas vacías por puesto
          // cuando `allowCreateEmptyRows` está habilitado. De lo contrario dejamos la tabla vacía.
          if (this.allowCreateEmptyRows) {
            this.puestoService.getPuestos().subscribe({ next: (puestos: any) => {
              const fullRows = (puestos||[]).map((p:any)=> ({ puesto: p.id, puesto_detalle: p, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' }));
              this.rows = fullRows;
            }});
          } else {
            this.rows = [];
          }
        }
          this.loading = false;
          
          try { this.weekStartChange.emit(this.weekStart); } catch(e){}
        },
        error: () => this.loading = false
      });
  }

  loadWeeksForMonth(mes: number, anio: number){
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }

    this.weeks = weeksLocal;
    const idx = this.weeks.indexOf(this.weekStart);
    this.currentWeekIndex = idx >= 0 ? idx : 0;
    if (this.weeks.length){
      this.weekStart = this.weeks[this.currentWeekIndex] || this.weeks[0];
    } else {
      this.weekStart = '';
    }
    this.loadWeek();
  }

  prevWeek(){
    if(this.currentWeekIndex > 0){
      this.currentWeekIndex -= 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
  }

  nextWeek(){
    if(this.currentWeekIndex < this.weeks.length - 1){
      this.currentWeekIndex += 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
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
      .subscribe({ next: () => this.loadWeek() });
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

  dayKeyFromDate(dateStr: string): string {
    // dateStr expected in YYYY-MM-DD
    if(!dateStr) return '';
    try {
      const parts = dateStr.split('-').map(Number);
      if (parts.length !== 3) return '';
      const d = new Date(parts[0], parts[1]-1, parts[2]);
      const map = ['sun','mon','tue','wed','thu','fri','sat'];
      return map[d.getDay()];
    } catch (e) {
      return '';
    }
  }
  
  computeWeekDays(): void {
    this.weekDays = [];
    if (!this.weekStart) return;
    const parts = this.weekStart.split('-').map(Number);
    if (parts.length !== 3) return;
    const base = new Date(parts[0], parts[1]-1, parts[2]);
    const month = base.getMonth();
    const shortOrder = ['Do','Lu','Ma','Mi','Ju','Vi','Sá'];
    const fullOrder = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

    for (let i = 0; i < 7; i++){
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const dow = d.getDay();
      if (d.getMonth() === month){
        this.weekDays.push({
          short: shortOrder[dow],
          name: fullOrder[dow],
          date: this.formatDateLocal(d),
          dayNum: d.getDate()
        });
      } else {
        this.weekDays.push({ short:'', name:'', date:'', dayNum:0 });
      }
    }
  }

}
