import { Injectable } from '@angular/core';
import * as ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';

@Injectable({
  providedIn: 'root'
})
export class ExcelService {

  private formatDate(d: Date) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private dayName(d: Date) {
    // Ajusta a español si quieres: ['D','L','M','M','J','V','S']
    return ['D','L','M','M','J','V','S'][d.getDay()];
  }

  async exportCalendar(
    rows: Array<{ name: string, assignments: Record<string,string> }>,
    startDate?: Date,
    weeks: number = 4,
    fileName: string = 'asignaciones.xlsx'
  ) {
    try {
      const start = startDate ? new Date(startDate) : new Date();
      start.setHours(0,0,0,0);

      // Normalize start to Monday (opcional). Aquí dejamos tal cual para empezar en la fecha dada.
      const totalDays = weeks * 7;
      const dates: Date[] = [];
      for (let i = 0; i < totalDays; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        dates.push(d);
      }

      const workbook = new ExcelJS.Workbook();
      const sheet = workbook.addWorksheet('Calendario');

      // Column for names
      const cols = [{ header: 'Nombre', key: 'name', width: 30 }];
      dates.forEach(dt => cols.push({ header: this.formatDate(dt), key: this.formatDate(dt), width: 12 }));
      sheet.columns = cols as any;

      // Row 1: months merged
      let colIndex = 2; // columna 1 es Nombre
      while (colIndex <= totalDays + 1) {
        const date = dates[colIndex - 2];
        const month = date.getMonth();
        // find run length of same month
        let run = 1;
        while (colIndex - 2 + run < dates.length && dates[colIndex - 2 + run].getMonth() === month) {
          run++;
        }
        const from = colIndex;
        const to = colIndex + run - 1;
        const monthName = date.toLocaleString('es-ES', { month: 'long' }).toUpperCase();
        sheet.mergeCells(1, from, 1, to);
        const cell = sheet.getCell(1, from);
        cell.value = monthName;
        cell.alignment = { horizontal: 'center', vertical: 'middle' };
        colIndex += run;
      }

      // Row 2: day names
      const dayRow = sheet.getRow(2);
      dayRow.getCell(1).value = '';
      dates.forEach((d, i) => {
        dayRow.getCell(i + 2).value = this.dayName(d);
        dayRow.getCell(i + 2).alignment = { horizontal: 'center' };
      });

      // Row 3: day numbers
      const dateRow = sheet.getRow(3);
      dateRow.getCell(1).value = '';
      dates.forEach((d, i) => {
        dateRow.getCell(i + 2).value = d.getDate();
        dateRow.getCell(i + 2).alignment = { horizontal: 'center' };
      });

      // Freeze panes: primera columna + primeras 3 filas
      sheet.views = [{ state: 'frozen', xSplit: 1, ySplit: 3 }];

      // Fill rows with data
      rows.forEach((r, ri) => {
        const excelRow = sheet.getRow(4 + ri);
        excelRow.getCell(1).value = r.name;
        excelRow.height = 18;
        dates.forEach((d, di) => {
          const key = this.formatDate(d);
          const val = r.assignments && r.assignments[key] ? r.assignments[key] : '';
          const cell = excelRow.getCell(2 + di);
          cell.value = val;
          cell.alignment = { horizontal: 'center', vertical: 'middle' };
          cell.border = {
            top: { style: 'thin' },
            left: { style: 'thin' },
            bottom: { style: 'thin' },
            right: { style: 'thin' }
          };
          // ejemplo de color por valor (ajusta según tus códigos)
          if (val === 'F') {
            cell.fill = { type: 'pattern', pattern:'solid', fgColor:{argb:'FFFFFF66'} }; // amarillo (ARGB)
          } else if (val === 'D') {
            cell.fill = { type: 'pattern', pattern:'solid', fgColor:{argb:'FF99CCFF'} }; // celeste
          } else if (val && val.startsWith('NK')) {
            cell.fill = { type: 'pattern', pattern:'solid', fgColor:{argb:'FFCCFFCC'} }; // verde claro
          }
        });
      });

      // Ajustes estéticos
      sheet.getRow(1).height = 18;
      sheet.getRow(2).height = 16;
      sheet.getRow(3).height = 16;

      const buf = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buf], { type: 'application/octet-stream' });
      saveAs(blob, fileName);
    } catch (err) {
      console.error('Error exportando Excel:', err);
      throw err;
    }
  }
}
