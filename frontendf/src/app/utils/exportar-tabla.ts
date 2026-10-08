// Descarga una tabla simple en Excel (encabezado azul, bordes, filtro y encabezado fijo) con lo que se ve en pantalla.
// La librería de Excel se carga SOLO al descargar (import dinámico): así no pesa al abrir la plataforma.
export async function exportarTablaExcel(
  hoja: string,
  columnas: Array<{ titulo: string; ancho: number }>,
  filas: any[][],
  archivo: string,
): Promise<void> {
  const ExcelJS: any = await import('exceljs');
  const { saveAs } = await import('file-saver');
  const wb = new (ExcelJS.Workbook || ExcelJS.default.Workbook)();
  const ws = wb.addWorksheet(hoja);
  ws.columns = columnas.map(c => ({ header: c.titulo, width: c.ancho }));
  filas.forEach(f => ws.addRow(f));
  const borde = { style: 'thin', color: { argb: 'FFBFC7D5' } };
  ws.eachRow((row: any, n: number) => {
    row.eachCell((cell: any) => {
      cell.border = { top: borde, left: borde, bottom: borde, right: borde };
      cell.alignment = { vertical: 'middle', wrapText: true };
      if (n === 1) {
        cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF0F2A4F' } };
        cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
      }
    });
  });
  ws.views = [{ state: 'frozen', ySplit: 1 }];
  ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: 1, column: columnas.length } };
  const buf = await wb.xlsx.writeBuffer();
  saveAs(new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), archivo);
}
