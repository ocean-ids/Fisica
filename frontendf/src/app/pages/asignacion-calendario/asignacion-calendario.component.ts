import { Component, OnInit, Output, EventEmitter } from '@angular/core';
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
  weekDays: Array<{short:string, name:string, date:string, dayNum:number}> = [];
  rows: any[] = [];
  loading = false;
  

  constructor(
    private asignacionCalendarioService: AsignacionCalendarioService,
    private puestoService: PuestoService,
    private asignacionService: AsignacionService
  ){}

  ngOnInit(): void {
    this.weekStart = this.computeCurrentMonday();
    this.loadWeek();
  }

  computeCurrentMonday(): string{
    const today = new Date();
    const day = today.getDay(); // 0 Domingo .. 6 Sab
    // calcular cuántos días restar para llegar al lunes (lunes=1)
    const diffFromMonday = (day + 6) % 7; // si es lunes -> 0, martes -> 1, etc.
    const monday = new Date(today);
    monday.setDate(today.getDate() - diffFromMonday);

    const y = monday.getFullYear();
    const m = String(monday.getMonth() + 1).padStart(2, '0');
    const d = String(monday.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
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

        
        if((!this.rows || this.rows.length === 0)){
          const parts = (this.weekStart||'').split('-').map(Number);
          const base = (parts.length===3) ? new Date(parts[0], parts[1]-1, parts[2]) : new Date();
          const mes = base.getMonth() + 1;
          const anio = base.getFullYear();

          
          this.puestoService.getPuestos().subscribe(puestos => {
            this.asignacionService.obtenerAsignaciones(mes, anio).subscribe(asigs => {
              const asignByPuesto: any = {};
              (asigs||[]).forEach((a:any)=>{ asignByPuesto[a.puesto] = asignByPuesto[a.puesto] || []; asignByPuesto[a.puesto].push(a); });

              const keys = ['mon','tue','wed','thu','fri','sat','sun'];
              const fullRows = puestos.map((p:any)=>{
                const list = asignByPuesto[p.id] || [];
                let chosen: any = null;
                if(list.length){
                 
                  chosen = list[0];
                }
                if(chosen && chosen.puesto_detalle){
                  const puesto = chosen.puesto_detalle;
                  const turno = (puesto.turno || '').toString().toLowerCase();
                  const default_code = turno.startsWith('n') ? 'N' : 'D';
                  const dias = puesto.dias || [];
                  const dias_norm = (dias||[]).map((d:any)=> String(d).trim().toLowerCase());
                  
                  const weekDayNames = this.weekDays.map(w=> (w.name||'').toString().toLowerCase());
                  const defaults: any = {};
                  for(let i=0;i<weekDayNames.length;i++){
                    const dayName = weekDayNames[i];
                    const match = dias_norm.some((d:string)=>{
                      if(!d) return false;
                      if(d.length<=2) return dayName.charAt(0) === d.charAt(0);
                      return d===dayName || dayName.indexOf(d)!==-1 || d.indexOf(dayName)!==-1;
                    });
                    defaults[keys[i]] = match ? default_code : '';
                  }
                  return { puesto: p.id, puesto_detalle: puesto, ...defaults };
                }
                return { puesto: p.id, puesto_detalle: p, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' };
              });
              this.rows = fullRows;
            });
          });
        }
          this.loading = false;
          
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
   
    const shortNames = ['Do','Lu','Ma','Mi','Ju','Vi','Sá'];
    const fullNames = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
    for (let i = 0; i < 7; i++){
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const wd = d.getDay(); 
      this.weekDays.push({
        short: shortNames[wd],
        name: fullNames[wd],
        date: d.toISOString().slice(0,10),
        dayNum: d.getDate()
      });
    }
  }

}
